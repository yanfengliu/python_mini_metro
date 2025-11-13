import os
import time
import argparse
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecNormalize, DummyVecEnv
from stable_baselines3.common.env_util import make_vec_env

from mini_plane_env import planeGameEnv

def run_agent(model_folder):
    """
    Loads and runs a trained PPO agent with a UI.
    """
    
    model_path = os.path.join(model_folder, "final_model.zip")
    stats_path = os.path.join(model_folder, "vec_normalize.pkl")

    if not os.path.exists(model_path):
        print(f"Warning: 'final_model.zip' not found. Searching for latest checkpoint...")
        checkpoints = [f for f in os.listdir(model_folder) if f.startswith("plane_rl_model_") and f.endswith(".zip")]
        if not checkpoints:
            print(f"Error: No model files found in {model_folder}. Aborting.")
            return
        
        checkpoints.sort(key=lambda f: int(f.split('_')[3]))
        model_path = os.path.join(model_folder, checkpoints[-1])
        print(f"Loading latest checkpoint: {model_path}")

    if not os.path.exists(stats_path):
        print(f"Error: 'vec_normalize.pkl' not found at {stats_path}. This file is required. Aborting.")
        return

    def create_eval_env():
        env = planeGameEnv(render_mode="human")
        env = gym.wrappers.TimeLimit(env, max_episode_steps=5000)
        return env

    env = DummyVecEnv([create_eval_env])

    env = VecNormalize.load(stats_path, env)
    env.training = False
    env.norm_reward = False

    print(f"Loading model from {model_path}...")
    model = PPO.load(model_path, env=env)
    print("Model loaded successfully.")

    obs = env.reset()
    total_reward = 0
    
    print("Starting simulation")
    try:
        while True:
            action, _states = model.predict(obs, deterministic=True)
            obs, reward, terminated, info = env.step(action)
            
            total_reward += reward[0]
            if terminated[0]:
                print(f"Episode finished. Total Reward: {total_reward}")
                total_reward = 0
                print("Resetting environment...")
                time.sleep(2)
                obs = env.reset()
                
    except KeyboardInterrupt:
        print("\nSimulation stopped by user.")
    finally:
        env.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a trained Mini plane PPO agent with UI.")
    parser.add_argument("model_folder", type=str, help="Path to the directory containing the saved model (.zip) and stats (vec_normalize.pkl).")
    
    args = parser.parse_args()
    
    run_agent(args.model_folder)