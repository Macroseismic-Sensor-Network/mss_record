import setuptools

# Get the current mss_record version, author and description.
for line in open('lib/mss_record/__init__.py').readlines():
    if (line.startswith('__version__')
            or line.startswith('__author__')
            or line.startswith('__authorEmail__')
            or line.startswith('__description__')
            or line.startswith('__license__')
            or line.startswith('__keywords__')
            or line.startswith('__website__')):
        exec(line.strip())

# Define the scripts to be processed.
scripts = ['scripts/mss_record',]


setuptools.setup(name = 'mss_record',
                 version           = __version__,
                 description       = __description__,
                 author            = __author__,
                 author_email      = __authorEmail__,
                 url               = __website__,
                 license           = __license__,
                 keywords          = __keywords__,
                 platforms         = 'any',
                 scripts           = scripts,
                 packages          = setuptools.find_packages(),
                 install_requires  = ['Adafruit-GPIO>=1.0.0'])

