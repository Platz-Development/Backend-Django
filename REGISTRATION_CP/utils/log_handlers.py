import gzip
import os
import shutil
from logging.handlers import RotatingFileHandler


class GZipRotatingFileHandler(RotatingFileHandler):
    """
    Rotates log files by size and compresses old logs with .gz
    """
    def doRollover(self):
        super().doRollover()

        # Compress all non-gz rotated logs
        log_dir = os.path.dirname(self.baseFilename)
        for filename in os.listdir(log_dir):
            full_path = os.path.join(log_dir, filename)

            if (
                filename.startswith(os.path.basename(self.baseFilename))
                and not filename.endswith(".gz")
                and filename != os.path.basename(self.baseFilename)
            ):
                with open(full_path, 'rb') as f_in, gzip.open(f'{full_path}.gz', 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
                os.remove(full_path)
