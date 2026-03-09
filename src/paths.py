from pathlib import Path

# Root folder
ROOT_FOLDER = Path(__file__).resolve().parent.parent

# Folder paths
CONFIG_FOLDER_PATH = ROOT_FOLDER / "config"
DEBUG_FOLDER_PATH = ROOT_FOLDER / "debug"
MISC_FOLDER_PATH = ROOT_FOLDER / "misc"
DOCS_FOLDER_PATH = ROOT_FOLDER / "docs"
SRC_FOLDER_PATH = ROOT_FOLDER / "src"
OUTPUT_FOLDER_PATH = ROOT_FOLDER / "output"
SQL_FOLDER_PATH = ROOT_FOLDER / "sql"

# Function to create folders
def get_or_create_folder(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path

# Automatically create all folders
CONFIG_FOLDER_PATH = get_or_create_folder(CONFIG_FOLDER_PATH)
DEBUG_FOLDER_PATH = get_or_create_folder(DEBUG_FOLDER_PATH)
MISC_FOLDER_PATH = get_or_create_folder(MISC_FOLDER_PATH)
DOCS_FOLDER_PATH = get_or_create_folder(DOCS_FOLDER_PATH)
SRC_FOLDER_PATH = get_or_create_folder(SRC_FOLDER_PATH)
OUTPUT_FOLDER_PATH = get_or_create_folder(OUTPUT_FOLDER_PATH)
SQL_FOLDER_PATH = get_or_create_folder(SQL_FOLDER_PATH)