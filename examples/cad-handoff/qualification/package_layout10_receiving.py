"""Package only the failed third and receiving fourth batches, retaining the first archive unchanged."""
from pathlib import Path
import package_layout10 as pack

if __name__=='__main__':
    pack.BASE=Path(__file__).resolve().parent/'layout-preparation-10'/'receiving-4'
    pack.BASE.mkdir(exist_ok=True)
    pack.FOLDERS=('native-3','native-4')
    pack.main()
