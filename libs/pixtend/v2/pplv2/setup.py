from setuptools import setup

setup(name='pixtendlibv2',
      version='0.1.3',
      description='Python modules for PiXtend V2 boards.',
      url='https://www.pixtend.de',
      author='Qube Solutions GmbH',
      author_email='info@pixtend.de',
      license='GPLv3 Open Source License',
      packages=['pixtendv2core', 'pixtendv2s', 'pixtendv2l'],
      zip_safe=False, install_requires=['spidev', 'RPi.GPIO'])
