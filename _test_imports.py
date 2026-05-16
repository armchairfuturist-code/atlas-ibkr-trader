import sys, os
sys.path.insert(0, r'C:\Users\Administrator\Documents\Projects\atlas-ibkr-trader')
print('Python', sys.version)
print('CWD', os.getcwd())

# Test imports step-by-step
try:
    import yfinance
    print('yfinance OK')
except Exception as e:
    print(f'yfinance FAIL: {e}')

try:
    import app
    print('app OK')
except Exception as e:
    print(f'app FAIL: {e}')

try:
    from app.layers.layer1_macro import MacroLayer
    print('MacroLayer OK')
except Exception as e:
    print(f'MacroLayer FAIL: {e}')
