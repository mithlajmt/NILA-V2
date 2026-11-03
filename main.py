import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from src.core.robot_controller import RobotController
from src.config.settings import Settings
from src.utils.logger import setup_logger

def main():
    """Main application entry point"""
    # Setup logging
    setup_logger()
    logger = logging.getLogger(__name__)

    # Single-instance process lock to prevent duplicate processes
    import fcntl
    import sys
    try:
        lock_file = open("/tmp/nila.lock", "w")
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (IOError, BlockingIOError):
        logger.warning("⚠️ Another instance of NILA-V2 is already running! Exiting immediately to prevent conflict.")
        sys.exit(0)
    
    # Load configuration
    settings = Settings()
    
    # Auto-connect Bluetooth speaker if configured
    mac = getattr(settings, "BT_SPEAKER_MAC", "41:42:84:29:F2:CE")
    if mac:
        import os, time
        os.system(f"echo 'connect {mac}' | bluetoothctl > /dev/null 2>&1")
        time.sleep(1.0)
    
    # Initialize robot controller
    robot = RobotController(settings)
    
    logger.info("🤖 STEP 1: Robot Greeting Test Starting...")
    logger.info(f"Mode: {settings.ENVIRONMENT}")
    logger.info(f"Voice Provider: {settings.SPEECH_PROVIDER}")
    
    try:
        # Start the robot (Step 1: Just greeting)
        asyncio.run(robot.start())
    except KeyboardInterrupt:
        logger.info("Robot stopped by user")
    except Exception as e:
        logger.error(f"Robot error: {e}")
    finally:
        robot.cleanup()

if __name__ == "__main__":
    main()
