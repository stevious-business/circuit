from circuitlogger import *
from configuration import *
from circuit import package_manager
from circuit.backend.project import Project
from circuit.backend.terminal import launch_terminal
from circuit.backend.server import launchServer
from thread_communicator import ServerData

if __name__ == "__main__":
    setup_logger()

    DBG.set(LOG_BASE)

    try:
        log(LOG_INFO, "Starting LCST!")
        log(LOG_DEBG, "Loading packages...")
        package_list = INCLUDED_PACKAGES
        package_datas = {}
        log(LOG_VERB, f"Located {len(package_list)} packages!")
        log_indent()
        loaded_package_count = 0
        for package in package_list:
            try:
                package_datas[package] = package_manager.load_package(package)
                loaded_package_count += 1
            except package_manager.InvalidPackageError as e:
                log(LOG_WARN, f"Package {package} failed to load! ({e})")
        log_dedent()
        log(LOG_DEBG, "Finished loading packages!")
        log(LOG_INFO, f"Successfully loaded {loaded_package_count}/{len(package_list)} packages!")
        print(package_datas)
        # TODO: Startup threads
        tc = ServerData(package_datas)
        tc.newThread("server", launchServer, daemon=False)
        # graphical thread and server thread startup here
        tc.startThreads()
        launch_terminal(tc)
        log(LOG_INFO, f"Exiting normally!")
        tc.join_threads()
    except KeyboardInterrupt:
        log(LOG_INFO, "Kill signal received, exiting...")
    finally:
        exit_logger()
