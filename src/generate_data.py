"""Simulation utilitaire de séries temporelles pour les tests unitaires et de validation."""
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]

def generate(seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(96)
    values = 1000 + 6*t + 175*np.sin(2*np.pi*t/12) + 65*np.cos(4*np.pi*t/12) + rng.normal(0,45,96)
    frame = pd.DataFrame({'date': pd.date_range('2018-01-01', periods=96, freq='MS'),
                          'demand': np.round(values, 2)})
    # Anomalies simulées pour tester les fonctions de nettoyage
    frame.loc[[8, 30, 54], 'demand'] = np.nan
    frame.loc[41, 'demand'] = -99
    frame = pd.concat([frame, frame.iloc[[17]]], ignore_index=True)
    return frame.sample(frac=1, random_state=seed).reset_index(drop=True)

if __name__ == '__main__':
    target = ROOT/'data/raw/monthly_demand.csv'
    target.parent.mkdir(parents=True, exist_ok=True)
    generate().to_csv(target, index=False)
    print(target)
