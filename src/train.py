import os
import time
import gymnasium as gym
import platform
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.vec_env import VecNormalize
from pilot_planning_env import PlaneGameEnv


LOG_DIR = f"logs/256-128-128/"
MODEL_DIR = f"models/PPO/256-128-128/"
TOTAL_TIMESTEPS = 25_000_000
SAVE_FREQ = 25_000

TB_LOG_NAME = "PPO_plane_Run"
net_arch_config = [256, 128, 128] 
policy_kwargs = dict(net_arch=net_arch_config)

def create_env():
    """Helper function to create and wrap the environment."""
    env = PlaneGameEnv(render_mode=None)
    env = gym.wrappers.TimeLimit(env, max_episode_steps=5000)
    return env

def train_agent():
    """Initializes and trains the PPO agent."""
    if __name__ == '__main__':
        os.makedirs(LOG_DIR, exist_ok=True)
        os.makedirs(MODEL_DIR, exist_ok=True)
        num_cpu = os.cpu_count() - 1 if os.cpu_count() > 1 else 1
        start_method = 'fork' if platform.system() != 'Windows' else 'spawn'
        env = make_vec_env(
            create_env,
            n_envs=num_cpu,
            vec_env_cls=SubprocVecEnv,
            vec_env_kwargs=dict(start_method=start_method)
        )

        env = VecNormalize(env, gamma=0.99)

        checkpoint_callback = CheckpointCallback(
            save_freq=SAVE_FREQ,
            save_path=MODEL_DIR,
            name_prefix="plane_rl_model",
            save_replay_buffer=True,
            save_vecnormalize=True,
        )

        checkpoint_callback = CheckpointCallback(
            save_freq=SAVE_FREQ,
            save_path=MODEL_DIR,
            name_prefix="plane_rl_model",
            save_replay_buffer=True,
            save_vecnormalize=True,
        )

        model = PPO(
            "MlpPolicy",
            env,
            verbose=1,
            tensorboard_log=LOG_DIR,
            device="cpu",
            n_steps=4096,
            learning_rate=1e-5,
            policy_kwargs=policy_kwargs,
            batch_size=64,
            gamma=0.99,
            gae_lambda=0.95,
            n_epochs=10,
            ent_coef=0.01,
            vf_coef=0.5,
            max_grad_norm=0.5,
        )

        print(f"Starting training on {num_cpu} cores for {TOTAL_TIMESTEPS} timesteps...")

        model.learn(
            total_timesteps=TOTAL_TIMESTEPS,
            callback=checkpoint_callback,
            tb_log_name=TB_LOG_NAME
        )

        final_model_path = os.path.join(MODEL_DIR, "final_model")
        model.save(final_model_path)
        env.save(os.path.join(MODEL_DIR, "vec_normalize.pkl"))
        print(f"Training complete! Final model saved to {final_model_path}")

        env.close()

if __name__ == '__main__':
    train_agent()
