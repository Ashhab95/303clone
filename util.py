from ast import arg
from glob import glob
from collections import defaultdict
import os, importlib, textwrap, sys, types

root_folder: str = os.path.dirname(os.path.abspath(__file__))
root_folder_name: str = os.path.basename(root_folder)

def get_ext_project_folder() -> str:
    """
    Returns the path to the external project folder.
    """

    # get parent directory of the current file
    current_dir = os.path.abspath(os.path.dirname(__file__))
    parent_dir = os.path.dirname(current_dir)

    # find all subfolders of parent_dir except this one
    subfolders = [f.path for f in os.scandir(parent_dir) if f.is_dir() and f.path != current_dir]
    # check which subfolder has a .git repo
    for folder in subfolders:
        if os.path.exists(os.path.join(folder, '.git')):
            break
    else:
        assert False, "No external project folder found. Did you set up your folder structure as seen in class?"

    return folder

def get_subclasses_from_file(filepath, base_classes, package_root):
    """
    Given the filepath to a Python source file, this function dynamically loads the module,
    then returns a dictionary for the classes defined in that module which inherit from the given classname.
    """

    def ensure_package_registered(package_name: str, package_root: str):
        if package_name not in sys.modules:
            pkg = types.ModuleType(package_name)
            pkg.__path__ = [package_root]
            sys.modules[package_name] = pkg

    package_root_folder = os.path.basename(package_root)

    ensure_package_registered(package_root_folder, package_root)

    rel_path = os.path.relpath(filepath, package_root)
    module_name = os.path.splitext(rel_path)[0].replace(os.sep, ".")
    
    full_module_name = package_root_folder + "." + module_name
    #print("Loading module", full_module_name, f"({package_root_folder}, {module_name}) from", filepath)

    spec = importlib.util.spec_from_file_location(
        full_module_name, filepath,
        submodule_search_locations=[os.path.dirname(filepath)]
    )
    assert spec, f"Could not load spec for {filepath}"
    
    module = importlib.util.module_from_spec(spec)    
    module.__package__ = full_module_name.rpartition('.')[0]

    try:
        spec.loader.exec_module(module)
    except:
        print("Error loading module", full_module_name, "from", filepath)
        return {}
    
    subclasses = defaultdict(dict)
    for name in dir(module):
        obj = getattr(module, name)
        for base_class in base_classes:
            #if isinstance(obj, type) and any("Map" in base.__name__ or "MapObject" not in base.__name__ for base in obj.__bases__):
            #    print("Found class", name, "in", filepath)
            #    print("  Inherits from", obj.__bases__)
            #    print("  Is subclass of", base_class, ":", issubclass(obj, base_class))
            #    print("  Is not base class:", obj is not base_class)
            #    #if "example" in name.lower():
            #    #    input()
            if isinstance(obj, type) and issubclass(obj, base_class) and obj is not base_class:
                subclasses[base_class][name] = obj
    return subclasses

def get_subclasses_from_folders(base_classes, verbose=False) -> dict:
    search_paths = [
        (root_folder_name, f'{root_folder_name}/maps/ext/'),
        (root_folder_name, f'{root_folder_name}/maps/'),
    ]
    if not any("server_remote" in arg for arg in sys.argv):
        ext_folder = get_ext_project_folder()
        search_paths.append((ext_folder, f'{ext_folder}/'))

    classes = {}
    for project_root, filepath in search_paths:
        files = list(glob(f"{filepath}/*.py"))
        if verbose: print(project_root, filepath, files)
        for file in files:
            if 'imports' in file: continue
            found_classes = get_subclasses_from_file(file, base_classes, project_root)
            for base_class, classes_ in found_classes.items():
                if base_class not in classes:
                    classes[base_class] = {}
                classes[base_class].update(classes_)
                if verbose: print("Found", len(classes_), "subclasses of", base_class, "in", file)
    for base_class, classes_ in classes.items():
        if verbose: print("Found", len(classes_), "subclasses of", base_class)
        assert len(classes_) > 0
        for name, cls in classes_.items():
            if verbose: print("  ", name, "->", cls)
    return classes

def shorten_lines(lines, max_length):
    short_lines = []
    for line in lines:
        if len(line) > max_length:
            short_lines.extend(textwrap.fill(line, max_length).split('\n'))
        else:
            short_lines.append(line)
    return short_lines

def get_valid_emails():
    if not os.path.exists('emails.csv'):
        return []

    valid_emails = set()
    with open('emails.csv') as f:
        for line in f:
            valid_emails.add(line.strip())
    return valid_emails