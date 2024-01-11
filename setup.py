from setuptools import setup
import os


if os.path.isfile('requirements.txt'):
    with open('requirements.txt', 'r') as requirements_file:
        install_requires = requirements_file.read().splitlines()
for package in install_requires:
    if package.startswith('git'):
        pname = package.split('/')[-1].split('.')[0]
        install_requires[install_requires.index(package)] = pname + ' @ ' + package
setup(
    name='timstof_targeted_3d_maldi_analysis',
    version='1.2.0',
    url='https://github.com/gtluubruker/timstof_targeted_3d_maldi_analysis',
    license='Apache License',
    author='Gordon T. Luu',
    author_email='gordon.luu@bruker.com',
    packages=['bin'],
    entry_points={'console_scripts': ['get_feature_intensities=bin.run:run']},
    install_requires=install_requires
)
