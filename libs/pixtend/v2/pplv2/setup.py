from setuptools import setup

setup(name='pixtendlibv2',
      version='0.1.4',
      description='Python modules for PiXtend V2 boards.',
      url='https://www.pixtend.de',
      author='Kontron Electronics GmbH',
      author_email='info@pixtend.de',
      license='MIT License',
      packages=['pixtendv2core', 'pixtendv2s', 'pixtendv2l'],
      zip_safe=False, install_requires=['spidev', 'RPi.GPIO'])
