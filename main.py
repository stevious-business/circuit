from circuitlogger import *

if __name__ == "__main__":
    setup_logger()

    DBG.set(LOG_BASE)

    try:
        log(LOG_INFO, "Starting LCST!")
    except KeyboardInterrupt:
        log(LOG_INFO, "Kill signal received, exiting...")
    finally:
        exit_logger()
