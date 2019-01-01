import logging

def setup_paths():
    import sys
    sys.path.extend([
        '/L/coding/tentacle',
        '/L/coding/spinboard',
        '/L/coding/reach',
    ])

# TODO name after some lizard?
def get_logger():
    return logging.getLogger('info-crawler')
