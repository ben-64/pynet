import sys
import logging
import importlib.util

# taken from rebus
log = logging.getLogger("pynet.importer")


def importer_for(path, prefix):
    def import_all(path=path, stop_on_error=False):
        import os
        import pkgutil
        folder = os.path.dirname(path)
        module = sys.modules[prefix]
        for _, name, _ in pkgutil.iter_modules([folder]):
            absname = prefix+"."+name
            if absname in sys.modules:
                continue
            submodule_spec = importlib.util.spec_from_file_location(absname, os.path.join(folder,name)+".py")
            if submodule_spec and submodule_spec.loader:
                try:
                    submodule = importlib.util.module_from_spec(submodule_spec)
                    #sys.modules[absname] = module
                    submodule_spec.loader.exec_module(submodule)
                except (ImportError,NotImplementedError) as e:
                    if stop_on_error:
                        raise
                    log.warning(f"Cannot load pynet plugin [{name}]. Root cause: {e}")
                else:
                    setattr(module, name, submodule)
            else:
                if stop_on_error:
                    raise ImportError(f"Cannot load pynet plugin [{name}]")

    return import_all
