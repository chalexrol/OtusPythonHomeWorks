import sys

def log_progress_update(progress):
    bar_length = 10
    status = ""
    progress = float(progress)
    if progress >= 1:
        progress = 1
        status = "Done.\r\n"
    block = int(round(bar_length * progress))
    text = "\rPercentage of log processing: [{0}] {1}% {2}".format("#" * block + "-" * (bar_length - block), round(progress * 100, 1),
                                              status)
    sys.stdout.write(text)
    sys.stdout.flush()
