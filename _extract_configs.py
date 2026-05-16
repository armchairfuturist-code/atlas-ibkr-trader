import subprocess
import os

base = r'C:\Users\Administrator\Documents\Projects\atlas-ibkr-trader'

configs = [
    ('configs/layers/base/layer1_macro.yaml', '_l1.yaml'),
    ('configs/layers/base/layer2_sector.yaml', '_l2.yaml'),
    ('configs/layers/base/layer3_superinvestors.yaml', '_l3.yaml'),
    ('configs/layers/base/layer4_decision.yaml', '_l4.yaml'),
]

for git_path, out_name in configs:
    r = subprocess.run(['git', 'cat-file', '-p', f'implementation:{git_path}'], capture_output=True, cwd=base)
    out_path = os.path.join(base, out_name)
    with open(out_path, 'wb') as f:
        f.write(r.stdout)
    print(f'{out_name}: {len(r.stdout)} bytes')
