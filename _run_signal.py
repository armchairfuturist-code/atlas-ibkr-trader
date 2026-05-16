import sys, os
sys.path.insert(0, r'C:\Users\Administrator\Documents\Projects\atlas-ibkr-trader')
os.chdir(r'C:\Users\Administrator\Documents\Projects\atlas-ibkr-trader')

import yaml
import logging
logging.basicConfig(level=logging.INFO, force=True)

from app.signal_orchestrator import SignalOrchestrator

config_path = r'C:\Users\Administrator\Documents\Projects\atlas-ibkr-trader\fixtures\config.paper.yaml'
with open(config_path) as f:
    config = yaml.safe_load(f)

universe_path = r'C:\Users\Administrator\Documents\Projects\atlas-ibkr-trader\fixtures\universe.valid.yaml'
with open(universe_path) as f:
    universe = yaml.safe_load(f)

all_tickers = universe.get('all', [])
print(f'Loaded {len(all_tickers)} tickers from universe')

orchestrator = SignalOrchestrator(config)
signals = orchestrator.generate_signals(tickers=all_tickers)

print(f'\nGenerated {len(signals)} signals')
print(f'{"Ticker":<8} {"Rating":<14} {"Conviction":<12} {"Direction":<10} {"Size%":<8} {"Source"}')
print('-' * 72)
for s in signals:
    print(f'{s.get("ticker","?"):<8} {s.get("rating","?"):<14} {s.get("conviction",0):<12} {s.get("direction","?"):<10} {s.get("size_pct",0):<8} {s.get("source_filter","")}')

print('\nDone.')
