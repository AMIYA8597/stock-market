import numpy as np
import gym
from gym import spaces
try:
    from stable_baselines3 import PPO, DQN, A2C
except ImportError:
    pass

class StockTradingEnv(gym.Env):
    def __init__(self, df, initial_balance=10000):
        super(StockTradingEnv, self).__init__()
        self.df = df
        self.initial_balance = initial_balance
        
        # 0 = Hold, 1 = Buy, 2 = Sell
        self.action_space = spaces.Discrete(3)
        
        # Observation space depends on columns in df
        obs_shape = df.shape[1]
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(obs_shape,), dtype=np.float32)
        self.reset()

    def reset(self):
        self.balance = self.initial_balance
        self.net_worth = self.initial_balance
        self.shares_held = 0
        self.current_step = 0
        return self._next_observation()

    def _next_observation(self):
        return self.df.iloc[self.current_step].values.astype(np.float32)

    def step(self, action):
        current_price = self.df.iloc[self.current_step]["close"]
        prev_net_worth = self.net_worth

        if action == 1: # Buy
            shares_bought = self.balance // current_price
            self.balance -= shares_bought * current_price
            self.shares_held += shares_bought
        elif action == 2: # Sell
            self.balance += self.shares_held * current_price
            self.shares_held = 0

        self.current_step += 1
        self.net_worth = self.balance + self.shares_held * current_price

        # Risk-adjusted reward (simple return)
        reward = self.net_worth - prev_net_worth
        done = self.current_step == len(self.df) - 1

        return self._next_observation(), reward, done, {}

class RLAgentTrainer:
    def __init__(self, env, algorithm="PPO"):
        self.env = env
        self.algorithm = algorithm.upper()
        if self.algorithm == "PPO":
            self.model = PPO("MlpPolicy", self.env, verbose=0)
        elif self.algorithm == "DQN":
            self.model = DQN("MlpPolicy", self.env, verbose=0)
        elif self.algorithm == "A2C":
            self.model = A2C("MlpPolicy", self.env, verbose=0)
        else:
            raise ValueError("Algorithm must be PPO, DQN, or A2C")

    def train(self, timesteps=10000):
        self.model.learn(total_timesteps=timesteps)
        
    def save(self, path):
        self.model.save(path)
        
    def predict(self, obs):
        action, _states = self.model.predict(obs)
        return action

