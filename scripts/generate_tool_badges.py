"""Create compact local tool badges; logos are embedded, not loaded by README.

Simple Icons / Devicon marks retain brand colors. Related Hugging Face and
PyTorch libraries use their ecosystem mark. Unbranded concepts use a plain
pictogram rather than an invented brand logo.
"""
from concurrent.futures import ThreadPoolExecutor
from html import escape
from pathlib import Path
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/tools'
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)

# filename, label, upstream Simple Icons slug (or @local ecosystem badge), accent
TOOLS = [
    ('numpy', 'NumPy', 'numpy', '#4DABCF'),
    ('pandas', 'Pandas', 'pandas', '#AAB5FF'),
    ('scipy', 'SciPy', 'scipy', '#8CAAE6'),
    ('matplotlib', 'Matplotlib', 'https://raw.githubusercontent.com/devicons/devicon/master/icons/matplotlib/matplotlib-original.svg', '#38BDF8'),
    ('seaborn', 'Seaborn', 'https://raw.githubusercontent.com/mwaskom/seaborn/master/doc/_static/logo-mark-lightbg.svg', '#68A8BD'),
    ('scikit-learn', 'Scikit-learn', 'scikitlearn', '#F7931E'),
    ('xgboost', 'XGBoost', None, '#22C55E'),
    ('lightgbm', 'LightGBM', None, '#86BC25'),
    ('tensorflow', 'TensorFlow', 'tensorflow', '#FF6F00'),
    ('keras', 'Keras', 'keras', '#EF5350'),
    ('torchvision', 'TorchVision', '@pytorch', '#EE4C2C'),
    ('pytorch-lightning', 'PyTorch Lightning', 'lightning', '#FBBF24'),
    ('transformers', 'Transformers', '@huggingface', '#FFD21F'),
    ('peft-lora', 'PEFT / LoRA', '@huggingface', '#FFD21F'),
    ('faiss', 'FAISS', None, '#38BDF8'),
    ('qdrant', 'Qdrant', 'qdrant', '#DC244C'),
    ('yolo', 'YOLO', 'ultralytics', '#38BDF8'),
    ('fastapi', 'FastAPI', 'fastapi', '#2DD4BF'),
    ('flask', 'Flask', 'flask', '#E6EDF3'),
    ('streamlit', 'Streamlit', 'streamlit', '#FF4B4B'),
    ('gradio', 'Gradio', 'gradio', '#F97316'),
    ('sql-server', 'SQL Server', 'https://raw.githubusercontent.com/devicons/devicon/master/icons/microsoftsqlserver/microsoftsqlserver-original.svg', '#EF4444'),
    ('mlflow', 'MLflow', 'mlflow', '#38BDF8'),
    ('wandb', 'Weights & Biases', 'weightsandbiases', '#FFBE00'),
    ('github-actions', 'GitHub Actions', 'githubactions', '#2088FF'),
    ('pytest', 'pytest', 'pytest', '#38BDF8'),
    ('linux', 'Linux', 'linux', '#FCC624'),
    ('bash', 'Bash', 'gnubash', '#4EAA25'),
    ('jupyter', 'Jupyter', 'jupyter', '#F37626'),
    ('colab', 'Google Colab', 'googlecolab', '#F9AB00'),
    ('conda', 'Conda', 'anaconda', '#44A833'),
    ('kaggle', 'Kaggle', 'kaggle', '#20BEFF'),
    ('aspnet-core', 'ASP.NET Core', 'dotnet', '#60A5FA'),
    ('html', 'HTML', 'html5', '#E34F26'),
    ('css', 'CSS', 'css', '#38BDF8'),
    ('javascript', 'JavaScript', 'javascript', '#F7DF1E'),
]


def pictogram(color, kind):
    shapes = {
        'tree': '<path d="M12 3v7M5 17v-7h14v7"/><circle cx="12" cy="3" r="2"/><rect x="2" y="17" width="6" height="5" rx="1"/><rect x="16" y="17" width="6" height="5" rx="1"/>',
        'plot': '<path d="M3 3v18h18M6 16l4-7 5 4 6-8"/><circle cx="10" cy="9" r="1.5"/><circle cx="15" cy="13" r="1.5"/>',
        'database': '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 4 18 4 18 0V5M3 12c0 4 18 4 18 0"/>',
        'search': '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6M7 8h6M7 11h4"/>',
        'code': '<path d="m8 5-6 7 6 7m8-14 6 7-6 7m-3-17-2 20"/>',
    }
    return ET.fromstring(f'<svg xmlns="{NS}" viewBox="0 0 24 24"><g fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{shapes[kind]}</g></svg>')


def build(tool):
    name, label, slug, color = tool
    icon = None
    if slug and slug.startswith('@'):
        local = OUT / (slug[1:] + '.svg')
        if local.exists():
            icon = ET.parse(local).getroot().find('{' + NS + '}svg')
        else:
            slug = slug[1:]
    if icon is None and slug:
        url = slug if slug.startswith('https://') else f'https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/{slug}.svg'
        try:
            with urllib.request.urlopen(url, timeout=25) as response:
                icon = ET.fromstring(response.read())
            icon.set('fill', color)
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
    if icon is None:
        kind = ('tree' if name in ['xgboost', 'lightgbm'] else
                'plot' if name in ['matplotlib', 'seaborn'] else
                'database' if name == 'sql-server' else
                'search' if name == 'faiss' else 'code')
        icon = pictogram(color, kind)
    icon.attrib.update(x='12', y='9', width='20', height='20')
    width = 54 + round(len(label) * 7.2)
    root = ET.fromstring(f'<svg xmlns="{NS}" width="{width}" height="38" viewBox="0 0 {width} 38" role="img"><title>{escape(label)}</title><rect x=".5" y=".5" width="{width-1}" height="37" rx="8" fill="#161B22" stroke="#30363D"/></svg>')
    root.append(icon)
    text = ET.SubElement(root, '{' + NS + '}text', {
        'x': '42', 'y': '24', 'font-family': 'Segoe UI,Arial,sans-serif',
        'font-size': '13', 'fill': '#E6EDF3',
    })
    text.text = label
    (OUT / (name + '.svg')).write_text(ET.tostring(root, encoding='unicode'), encoding='utf-8')
    return name


if __name__ == '__main__':
    referenced = set(re.findall(r'\./assets/tools/([a-z0-9-]+)\.svg',
                                (ROOT / 'README.md').read_text(encoding='utf-8')))
    with ThreadPoolExecutor(max_workers=6) as pool:
        completed = list(pool.map(build, [tool for tool in TOOLS if tool[0] in referenced]))
    print(f'Created {len(completed)} local tool badges.')
