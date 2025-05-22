# handling path
import os
import sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pygame
import random
from typing import List, Dict, Tuple, Optional # Added for type hinting

# 游戏特定导入 (根据你的项目结构调整路径)
from config import (
    num_metros, num_paths, num_stations_max, station_spawning_interval_step,
    framerate, screen_color, screen_width, screen_height,
    station_grid_size, station_capacity, 
)
# 以下常量至关重要，假设在 config.py 中定义:
NUM_HORIZONTAL_GRIDS, NUM_VERTICAL_GRIDS = station_grid_size
STATION_MAX_CAPACITY= station_capacity# 或从 Station/Metro 类获取 (如果是静态成员)
from geometry.type import ShapeType # 假设 ShapeType 是一个枚举
from mediator import Mediator, MeditatorState # 游戏逻辑核心
from visuals.background import draw_waves # 如果环境直接用于渲染背景波浪

# Stable Baselines3 用于训练和评估
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.callbacks import EvalCallback #, StopTrainingOnRewardThreshold


class MiniMetroSimpleEnv(gym.Env):
    metadata = {'render_modes': ['human', 'rgb_array'], 'render_fps': framerate or 30}

    def __init__(self, gamespeed: int = 1, visuals: bool = False, is_eval_env: bool = False):
        super().__init__()

        # 确保 Pygame 字体已初始化
        if not pygame.font.get_init():
            pygame.font.init()
        # 如果需要视觉效果，确保 Pygame 已初始化
        if visuals and not pygame.get_init():
             pygame.init()

        self.mediator = Mediator(gamespeed=gamespeed, gen_stations_first=False)
        
        self.max_station_slots = num_stations_max
        self.max_paths = num_paths 
        self.shape_types_enum: List[ShapeType] = list(ShapeType) # ShapeType 枚举的成员列表
        self.num_shape_types = len(self.shape_types_enum)

        self.visuals = visuals
        self.is_eval_env = is_eval_env
        self.screen: Optional[pygame.Surface] = None
        self.clock: Optional[pygame.time.Clock] = None
        if self.visuals:
            if not pygame.display.get_init(): # 确保显示模块已初始化
                 pygame.display.init()
            self.screen = pygame.display.set_mode((screen_width, screen_height))
            pygame.display.set_caption("Mini Metro RL (Simple Env)")
            self.clock = pygame.time.Clock()

        # --- 动作空间 ---
        # 0: NO_OP
        # 1: DELETE_ALL_COMPLETED_PATHS
        # 2: FINISH_PATH_IN_PROGRESS
        # 3: CLEAR_PATH_IN_PROGRESS
        # 4 to 3+max_station_slots: ADD_STATION_SLOT_idx_TO_PATH_IN_PROGRESS
        self.num_action_types_exclusive_of_add_station = 4
        self.action_space = spaces.Discrete(self.num_action_types_exclusive_of_add_station + self.max_station_slots)

        # --- 状态空间 (观测空间) ---
        # 1. 站点特征 (每个槽位)
        #    exists(1), shape_one_hot(num_shapes), passenger_dest_profile(num_shapes),
        #    is_in_current_path(1), is_start_current(1), is_last_current(1)
        self.station_feature_size = 1 + self.num_shape_types + self.num_shape_types + 1 + 1 + 1
        obs_size_stations = self.max_station_slots * self.station_feature_size

        # 2. 连接矩阵 (站点槽位之间的邻接矩阵)
        obs_size_connectivity = self.max_station_slots * self.max_station_slots

        # 3. 全局 / 当前构建线路信息
        #    num_existing_paths_norm(1), len_current_path_norm(1), score_norm(1)
        obs_size_global = 3
        
        self.total_obs_size = obs_size_stations + obs_size_connectivity + obs_size_global
        self.observation_space = spaces.Box(low=-1.0, high=1.0, shape=(self.total_obs_size,), dtype=np.float32)

        # 环境内部状态，用于智能体构建线路
        self.current_path_slot_indices: List[int] = [] # 存储观测空间中的站点槽位索引
        self.current_path_potential_loop: bool = False # 当前构建的线路是否可能形成环路

        self.last_score = 0
        self.current_rl_step = 0 # 当前 RL episode 中的步数
        
        self.game_ticks_per_rl_step = 15 # 每个 RL 动作后，游戏模拟多少个 tick
        self.max_rl_steps_per_episode = 1500 # RL episode 的最大长度，用于 truncated

    def _get_obs(self) -> np.ndarray:
        obs = np.zeros(self.total_obs_size, dtype=np.float32)
        obs_idx_ptr = 0 # 当前观测向量的写入位置

        # --- 1. 站点特征 ---
        # 创建一个从活动站点对象 ID 到其在观测中槽位索引的映射，用于快速查找
        # 注意：这里的槽位索引是 self.mediator.stations 列表中的索引
        active_station_id_to_slot_map: Dict[int, int] = {
            id(self.mediator.stations[i]): i 
            for i in range(len(self.mediator.stations))
            if i < self.max_station_slots # 确保不超过观测空间定义的最大站点数
        }

        for s_slot_idx in range(self.max_station_slots):
            # 判断此槽位是否有真实存在的站点
            station_exists = (s_slot_idx < len(self.mediator.stations))
            
            # 记录当前站点特征的起始写入位置，方便填充0（如果站点不存在）
            # start_station_features_ptr = obs_idx_ptr 

            # 特征: exists (是否存在)
            obs[obs_idx_ptr] = 1.0 if station_exists else 0.0
            obs_idx_ptr += 1

            if station_exists:
                station = self.mediator.stations[s_slot_idx] # 获取真实的站点对象
                
                # 特征: shape_one_hot (站点形状的独热编码)
                shape_one_hot = np.zeros(self.num_shape_types, dtype=np.float32)
                try:
                    s_type_idx = self.shape_types_enum.index(station.shape.type)
                    shape_one_hot[s_type_idx] = 1.0
                except ValueError: pass # 如果形状不在预定义的列表中，则跳过 (理论上不应发生)
                obs[obs_idx_ptr : obs_idx_ptr + self.num_shape_types] = shape_one_hot
                obs_idx_ptr += self.num_shape_types

                # 特征: passenger_dest_profile (站点中等待前往各目标形状的乘客数量，已标准化)
                pass_dest_profile = np.zeros(self.num_shape_types, dtype=np.float32)
                for passenger in station.passengers:
                    try:
                        # 获取乘客目标形状在形状枚举列表中的索引
                        dest_type_idx = self.shape_types_enum.index(passenger.destination_shape.type)
                        pass_dest_profile[dest_type_idx] += 1.0
                    except ValueError: pass
                # 标准化：除以站点最大容量
                obs[obs_idx_ptr : obs_idx_ptr + self.num_shape_types] = pass_dest_profile / (STATION_MAX_CAPACITY + 1e-6)
                obs_idx_ptr += self.num_shape_types

                # 特征: is_in_current_path_being_built (此站点是否在当前构建的线路中)
                obs[obs_idx_ptr] = 1.0 if s_slot_idx in self.current_path_slot_indices else 0.0
                obs_idx_ptr += 1
                # 特征: is_start_of_current_path (是否为当前构建线路的起点)
                obs[obs_idx_ptr] = 1.0 if self.current_path_slot_indices and self.current_path_slot_indices[0] == s_slot_idx else 0.0
                obs_idx_ptr += 1
                # 特征: is_last_in_current_path (是否为当前构建线路的最新加入站点)
                obs[obs_idx_ptr] = 1.0 if self.current_path_slot_indices and self.current_path_slot_indices[-1] == s_slot_idx else 0.0
                obs_idx_ptr += 1
            else: # 如果此槽位没有站点，用0填充剩余特征
                # 'exists' 特征已设为0.0
                # 需要填充的剩余特征数量 = self.station_feature_size - 1 (减去 'exists' 特征)
                remaining_features_count = self.station_feature_size - 1
                obs[obs_idx_ptr : obs_idx_ptr + remaining_features_count] = 0.0
                obs_idx_ptr += remaining_features_count
        
        # --- 2. 连接矩阵 ---
        # adj[i,j] = 1.0 表示观测槽位 i 中的站点在某条 *已完成* 线路中直接连接到观测槽位 j 中的站点
        adj_matrix = np.zeros((self.max_station_slots, self.max_station_slots), dtype=np.float32)
        for path in self.mediator.paths: # 遍历所有已完成的线路
            if len(path.stations) >= 2: # 至少需要两个站点才能构成连接
                for k_path_idx in range(len(path.stations) - 1): # 遍历线路中的站点对
                    station_A_obj = path.stations[k_path_idx]
                    station_B_obj = path.stations[k_path_idx+1]
                    
                    # 将站点对象映射到它们在观测空间的槽位索引
                    obs_slot_A = active_station_id_to_slot_map.get(id(station_A_obj), -1)
                    obs_slot_B = active_station_id_to_slot_map.get(id(station_B_obj), -1)

                    if obs_slot_A != -1 and obs_slot_B != -1: # 确保两个站点都在当前观测槽位中
                        adj_matrix[obs_slot_A, obs_slot_B] = 1.0 # 标记连接
                
                if path.is_looped and len(path.stations) >=2: # 如果是环线，最后一个站点连接到第一个
                    station_Last_obj = path.stations[-1]
                    station_First_obj = path.stations[0]
                    obs_slot_Last = active_station_id_to_slot_map.get(id(station_Last_obj), -1)
                    obs_slot_First = active_station_id_to_slot_map.get(id(station_First_obj), -1)
                    if obs_slot_Last != -1 and obs_slot_First != -1:
                         adj_matrix[obs_slot_Last, obs_slot_First] = 1.0
        
        obs[obs_idx_ptr : obs_idx_ptr + adj_matrix.size] = adj_matrix.flatten() # 展平连接矩阵并加入观测
        obs_idx_ptr += adj_matrix.size

        # --- 3. 全局 / 当前构建线路信息 ---
        # 特征: num_existing_paths_norm (已完成线路数量，标准化)
        obs[obs_idx_ptr] = len(self.mediator.paths) / self.max_paths if self.max_paths > 0 else 0.0
        obs_idx_ptr += 1
        # 特征: len_current_path_norm (当前构建线路的长度，标准化)
        obs[obs_idx_ptr] = len(self.current_path_slot_indices) / self.max_station_slots if self.max_station_slots > 0 else 0.0
        obs_idx_ptr += 1
        # 特征: score_norm (当前分数，简单标准化)
        obs[obs_idx_ptr] = self.mediator.score / (self.mediator.steps + 1e-5) # 防止除以0
        obs_idx_ptr += 1
        
        return np.clip(obs, -1.0, 1.0) # 确保观测值在 [-1, 1] 范围内

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None):
        super().reset(seed=seed) # 处理gymnasium内部的随机种子
        
        # 如果是评估环境且未提供种子，使用固定种子以保证评估的可复现性
        if seed is None and self.is_eval_env:
            seed = 42 
        
        if seed is not None:
            self.mediator.seed = seed # 设置游戏逻辑核心的种子
            random.seed(seed)         # 设置Python内置random的种子
            np.random.seed(seed)      # 设置NumPy的种子

        self.mediator.reset_progress() # 重置游戏逻辑状态
        self.last_score = 0
        self.current_rl_step = 0
        self.current_path_slot_indices = []
        self.current_path_potential_loop = False

        # 游戏开始时，通常会有几个初始站点。让游戏模拟运行几步以生成它们。
        initial_dt_ms = 1000 // (framerate or 30) 
        for _ in range(10): # 模拟一小段时间
            # Mini Metro 通常以3个站点开始，或者达到最大站点数的一小部分
            if len(self.mediator.stations) >= min(3, self.max_station_slots):
                break
            self.mediator.increment_time(initial_dt_ms)
        
        # 如果有站点了，再运行一小步，确保乘客生成逻辑有机会运行
        if len(self.mediator.stations) > 0:
            self.mediator.increment_time(1)


        observation = self._get_obs()
        info = self._get_info()
        self.last_score = self.mediator.score # 重置后，根据初始状态更新分数
        return observation, info

    def step(self, action: int):
        reward = 0.0
        terminated = False  # 游戏是否因为失败（如站点爆满）而结束
        truncated = False   # 游戏是否因为达到最大步数等非失败原因而结束
        invalid_action_penalty = -0.05 # 对无效或不合理操作的惩罚

        # --- 解析并执行动作 ---
        if action == 0: # NO_OP (无操作)
            pass
        elif action == 1: # DELETE_ALL_COMPLETED_PATHS (删除所有已完成的线路)
            paths_to_cancel = list(self.mediator.paths) # 复制列表以避免在迭代时修改
            for path in paths_to_cancel:
                self.mediator.cancel_path(path)
            # 此操作的奖励/惩罚会通过未来的分数变化间接体现
        elif action == 2: # FINISH_PATH_IN_PROGRESS (完成当前正在构建的线路)
            if len(self.current_path_slot_indices) >= 2: # 至少需要2个站点才能构成有效线路
                if len(self.mediator.paths) < self.max_paths: # 检查是否有可用的线路槽位
                    # 将存储的站点槽位索引转换为真实的站点对象
                    actual_stations_in_path: List = [] # 使用类型 Any, 因为 Station 类型未在此处定义
                    valid_path_conversion = True
                    for slot_idx in self.current_path_slot_indices:
                        if slot_idx < len(self.mediator.stations): # 确保槽位索引仍然有效
                            actual_stations_in_path.append(self.mediator.stations[slot_idx])
                        else:
                            valid_path_conversion = False # 索引失效（例如站点消失了）
                            break
                    
                    if valid_path_conversion and len(actual_stations_in_path) >=2 : # 再次检查转换后的路径有效性
                        # 使用 Mediator 的方法来构建线路
                        self.mediator.start_path_on_station(actual_stations_in_path[0])
                        for station_obj in actual_stations_in_path[1:]:
                            self.mediator.add_station_to_path(station_obj)
                        # Mediator 的 add_station_to_path 和 finish_path_creation 会处理环路逻辑
                        self.mediator.finish_path_creation()
                        reward += 0.2 # 成功创建线路给予少量奖励
                        self.current_path_slot_indices = [] # 清空当前构建的线路
                        self.current_path_potential_loop = False
                    else: # 路径在转换过程中变得无效
                        reward += invalid_action_penalty * 2 
                        self.current_path_slot_indices = [] 
                        self.current_path_potential_loop = False
                else: # Mediator 中没有可用的线路槽位
                    reward += invalid_action_penalty 
            else: # 当前构建的线路太短，无法完成
                reward += invalid_action_penalty
                self.current_path_slot_indices = [] 
                self.current_path_potential_loop = False
        elif action == 3: # CLEAR_PATH_IN_PROGRESS (清除/放弃当前正在构建的线路)
            # if self.current_path_slot_indices: # 如果确实有线路被放弃
            #     reward -= 0.02 # 放弃部分构建的线路给予微小惩罚
            self.current_path_slot_indices = []
            self.current_path_potential_loop = False
        else: # ADD_STATION_SLOT_idx_TO_PATH_IN_PROGRESS (添加站点到当前构建线路)
            # 从动作值计算站点槽位索引
            slot_idx_to_add = action - self.num_action_types_exclusive_of_add_station
            
            # 检查索引是否有效，并且该槽位确实有站点存在
            if 0 <= slot_idx_to_add < self.max_station_slots and \
               slot_idx_to_add < len(self.mediator.stations):
                
                if not self.current_path_slot_indices: # 如果是开始构建新线路
                    self.current_path_slot_indices.append(slot_idx_to_add)
                    self.current_path_potential_loop = False
                else: # 添加到已开始的线路
                    if slot_idx_to_add != self.current_path_slot_indices[-1]: # 不能连续添加同一个站点
                        self.current_path_slot_indices.append(slot_idx_to_add)
                        # 检查是否形成潜在环路
                        if len(self.current_path_slot_indices) > 1 and \
                           slot_idx_to_add == self.current_path_slot_indices[0]:
                            self.current_path_potential_loop = True
                        else: # 如果不是环路，或者添加的不是起点，则重置环路可能标志
                            self.current_path_potential_loop = False
                    else: # 尝试连续添加同一个站点
                        reward += invalid_action_penalty * 0.5
            else: # 无效的站点槽位索引 (例如，槽位为空或索引越界)
                reward += invalid_action_penalty
        
        # --- 模拟游戏运行 ---
        game_outcome_state = MeditatorState.RUNNING
        dt_ms = 1000 // (framerate or 30) 
        
        for _ in range(self.game_ticks_per_rl_step):
            if self.visuals and self.screen: # 如果开启视觉效果，处理Pygame事件（如关闭窗口）
                for pygame_event in pygame.event.get():
                    if pygame_event.type == pygame.QUIT:
                        terminated = True; break
            if terminated: break # 如果用户关闭窗口，则提前结束
            
            game_outcome_state = self.mediator.increment_time(dt_ms) #推进游戏逻辑
            if game_outcome_state == MeditatorState.ENDED: # 检查游戏是否结束 (失败)
                terminated = True; break
        
        # --- 计算奖励 ---
        reward += (self.mediator.score - self.last_score) # 主要奖励：分数变化
        self.last_score = self.mediator.score

        if terminated and game_outcome_state == MeditatorState.ENDED: # 如果游戏因失败而结束
            reward -= 10.0 # 较大的惩罚

        # 可选：对站点拥挤情况进行惩罚
        num_crowded_stations = sum(1 for s in self.mediator.stations if len(s.passengers) > 0.8 * STATION_MAX_CAPACITY)
        reward -= num_crowded_stations # 对每个拥挤的站点进行微小惩罚
        num_passengers = sum(len(s.passengers) for s in self.mediator.stations)
        reward -= num_passengers * 0.05 

        # --- 更新 RL 步数并检查是否达到 episode 最大长度 ---
        self.current_rl_step += 1
        if self.current_rl_step >= self.max_rl_steps_per_episode:
            truncated = True # 达到最大步数，episode 截断
            if not terminated : # 如果不是因为游戏失败而截断，可以给予少量负反馈
                 reward -= 0.5


        observation = self._get_obs() # 获取新的状态观测
        info = self._get_info()       # 获取辅助信息

        if self.visuals: # 如果开启视觉效果，渲染当前帧
            self.render()
            
        return observation, reward, terminated, truncated, info

    def render(self):
        # 如果没有开启视觉效果，并且渲染模式中不包含 'rgb_array'，则不执行渲染
        if not self.visuals and 'rgb_array' not in self.metadata['render_modes']:
            return None
        
        # 如果屏幕对象未初始化 (例如，仅为 'rgb_array' 模式且未进行 'human' 模式渲染)
        if self.screen is None: 
            if not pygame.display.get_init(): pygame.display.init() # 确保显示模块已初始化
            # 创建一个离屏表面用于渲染，这样即使没有窗口也能得到图像数据
            self.screen = pygame.Surface((screen_width, screen_height)) 
        
        # 通用渲染流程
        self.screen.fill(screen_color) # 填充背景色
        # 检查 draw_waves 是否可用并且可调用，然后渲染背景波浪
        if 'draw_waves' in globals() and callable(draw_waves): 
             draw_waves(self.screen, self.mediator.time_ms)
        self.mediator.render(self.screen) # Mediator 负责绘制所有游戏实体

        # 如果是 'human' 渲染模式并且开启了视觉效果，则更新到屏幕上显示
        if 'human' in self.metadata['render_modes'] and self.visuals:
            pygame.display.flip() # 更新整个屏幕
            if self.clock: self.clock.tick(self.metadata['render_fps']) # 控制帧率
            return None # 'human' 模式下 render 通常返回 None
        
        # 如果是 'rgb_array' 渲染模式，返回屏幕图像的NumPy数组
        if 'rgb_array' in self.metadata['render_modes']:
            # 将 Pygame Surface 转换为 NumPy 数组，并调整维度顺序 (W,H,C) -> (H,W,C)
            return pygame.surfarray.array3d(self.screen).transpose(1, 0, 2) 
        
        return None # 其他情况或默认不返回

    def _get_info(self) -> Dict: # 返回包含辅助信息的字典
        return {
            "score": self.mediator.score,
            "total_game_ticks": self.mediator.steps,    # Mediator 内部的游戏 tick 数
            "rl_episode_steps": self.current_rl_step, # 当前 RL episode 的步数
            "num_stations": len(self.mediator.stations),
            "num_completed_paths": len(self.mediator.paths),
            "path_in_progress_len": len(self.current_path_slot_indices),
            "passengers_waiting_total": sum(len(s.passengers) for s in self.mediator.stations),
        }

    def close(self): # 清理环境资源
        if self.visuals or (self.screen is not None): # 如果屏幕曾被初始化
            pygame.display.quit() # 关闭Pygame显示模块
        # pygame.font.quit() # 通常不需要单独关闭字体，pygame.quit()会处理
        # pygame.quit() # 如果应用中其他部分也使用Pygame，全局关闭可能不合适
        self.screen = None
        self.clock = None

# --- 训练与评估脚本示例 ---
def run_training(load=False):
    print("启动精简版 Mini Metro 环境的训练与评估...")

    # 创建环境实例
    # 训练时通常关闭视觉效果并加速游戏以提高效率
    train_env = MiniMetroSimpleEnv(visuals=False, gamespeed=10) 
    
    # (可选) 检查环境是否符合 Stable Baselines3 的规范
    # print("检查环境规范性...")
    # check_env(train_env) 
    # print("环境检查通过。")

    # 定义日志和模型保存路径
    log_dir = "./mini_metro_simple_rl_logs/"
    model_save_name = "ppo_mini_metro_simple"

    # 设置评估环境和回调函数
    # 使用与训练环境分开的评估环境是一个好习惯，通常 gamespeed=1
    eval_env = MiniMetroSimpleEnv(visuals=False, gamespeed=1, is_eval_env=True) 
    # EvalCallback 会定期评估模型，并保存表现最好的模型
    eval_callback = EvalCallback(eval_env, 
                                 best_model_save_path=log_dir + 'best_model/',
                                 log_path=log_dir + 'results/', 
                                 eval_freq=10000, # 每10000个 agent 步数评估一次
                                 deterministic=True, 
                                 render=False)

    # 定义强化学习 Agent (使用PPO算法)
    # 超参数可能需要根据实际情况调整，这里提供了一些常用值作为起点
    model = PPO("MlpPolicy",        # 使用多层感知机策略网络
                train_env,          # 训练环境
                verbose=1,          # 打印训练过程信息
                tensorboard_log=log_dir + "tensorboard/", # TensorBoard 日志路径
                gamma=0.99,         # 折扣因子
                gae_lambda=0.95,    # GAE lambda 参数
                n_steps=1024,       # 每个 rollout/update 收集的步数
                ent_coef=0.005,     # 熵正则化系数，鼓励探索
                learning_rate=2.5e-4, # 学习率
                vf_coef=0.5,        # 值函数损失系数
                max_grad_norm=0.5,  # 梯度裁剪范数
                batch_size=64,      # 每个 PPO epoch 的 minibatch 大小
                n_epochs=10,        # 每个 PPO update 的 epoch 数
                seed=42,            # 随机种子，保证训练可复现
                device='cpu
               )
    if load == True:
        final_model_path = log_dir + model_save_name + ".zip"
        model = PPO.load(final_model_path, env=train_env) # 评估时可以不传入env，policy会使用新env
        print(f"已加载模型: {final_model_path}")

    print(f"模型策略网络结构: {model.policy}")
    print(f"观测空间维度: {train_env.observation_space.shape}")
    print(f"动作空间大小: {train_env.action_space.n}")

    # 训练模型
    total_timesteps_to_train = 300000 # 总训练步数 (可根据需要调整)
    print(f"开始训练，总步数: {total_timesteps_to_train}...")
    try:
        model.learn(total_timesteps=total_timesteps_to_train, 
                    callback=eval_callback, # 在训练过程中加入评估回调
                    progress_bar=True)      # 显示训练进度条
        model.save(log_dir + model_save_name) # 保存最终模型
        print(f"训练完成。最终模型已保存到 {log_dir + model_save_name}")
    except Exception as e:
        print(f"训练过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally: # 确保环境被关闭
        train_env.close()
        eval_env.close()

    # --- 模型评估 ---
    print("\n--- 开始评估训练好的模型 ---")
    # 可以加载最终模型或EvalCallback保存的最佳模型
    try:
        # best_model_path = log_dir + 'best_model/best_model.zip' # .zip 后缀会自动添加
        # loaded_model = PPO.load(best_model_path, env=eval_env)
        # 如果没有best_model, 加载最后保存的
        final_model_path = log_dir + model_save_name + ".zip"
        loaded_model = PPO.load(final_model_path) # 评估时可以不传入env，policy会使用新env
        print(f"已加载模型: {final_model_path}")

        # 使用独立的评估环境
        eval_env_for_policy = MiniMetroSimpleEnv(visuals=False, gamespeed=1, is_eval_env=True)
        mean_reward, std_reward = evaluate_policy(loaded_model, 
                                                  eval_env_for_policy, 
                                                  n_eval_episodes=20, # 评估20个episodes
                                                  deterministic=True) # 使用确定性动作进行评估
        print(f"评估结果: 平均奖励: {mean_reward:.2f} +/- {std_reward:.2f}")
        eval_env_for_policy.close()
    except Exception as e:
        print(f"评估过程中发生错误: {e}")


def evaluation():
    
    # 定义日志和模型保存路径
    log_dir = "./mini_metro_simple_rl_logs/"
    model_save_name = "ppo_mini_metro_simple"
    # --- 使用训练好的模型进行可视化演示 ---
    print("\n--- 使用训练好的模型进行可视化演示 ---")
    try:
        # best_model_path = log_dir + 'best_model/best_model.zip'
        # loaded_model_visual = PPO.load(best_model_path)
        final_model_path = log_dir + model_save_name + ".zip"
        loaded_model_visual = PPO.load(final_model_path)

        env_visual = MiniMetroSimpleEnv(visuals=True, gamespeed=1, is_eval_env=True)
        obs_visual, _ = env_visual.reset()
        for episode in range(3): # 演示5个episodes
            terminated_visual = False
            truncated_visual = False
            episode_reward = 0
            current_step = 0
            while not (terminated_visual or truncated_visual):
                action_visual, _ = loaded_model_visual.predict(obs_visual, deterministic=True)
                obs_visual, reward_visual, terminated_visual, truncated_visual, info_visual = env_visual.step(action_visual)
                episode_reward += reward_visual
                # env_visual.render() # render() 会在 step() 中被调用（如果 visuals=True）
                if (terminated_visual or truncated_visual):
                    print(f"可视化演示 Episode {episode+1} 结束。最终得分: {info_visual['score']}, "
                          f"RL步数: {info_visual['rl_episode_steps']}, 总奖励: {episode_reward:.2f}")
                    obs_visual, _ = env_visual.reset() # 重置环境以开始下一个episode
                    break
        env_visual.close()
    except Exception as e:
        print(f"可视化演示过程中发生错误: {e}")


if __name__ == '__main__':
    # 确保必要的配置变量已定义 (通常在 config.py 中)
    # 这是一个示例检查，实际应用中你可能需要更完善的配置管理
    essential_configs_defined = True
    try:
        _ = NUM_HORIZONTAL_GRIDS
        _ = ShapeType
        _ = STATION_MAX_CAPACITY
    except NameError:
        essential_configs_defined = False
        print("错误：一些必要的配置变量 (如 NUM_HORIZONTAL_GRIDS, ShapeType, STATION_MAX_CAPACITY) 未定义。")
        print("请确保 'config.py' 文件存在于Python路径中，并且已正确定义这些变量。")
        print("脚本将中止。")
    
    if essential_configs_defined:
        #run_training(load=False)
        evaluation()