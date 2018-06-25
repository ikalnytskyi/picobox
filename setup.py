import os
import io
import setuptools


here = os.path.dirname(__file__)

with io.open(os.path.join(here, 'README.rst'), 'r', encoding='utf-8') as f:
    long_description = f.read()


setuptools.setup(
    name='picobox',
    description='Dependency injection framework designed with Python in mind.',
    long_description=long_description,
    url='https://github.com/ikalnytskyi/picobox',
    license='MIT',
    author='Ihor Kalnytskyi',
    author_email='ihor@kalnytskyi.com',
    packages=setuptools.find_packages(where='src'),
    package_dir={'': 'src'},
    use_scm_version={
        'root': here,
    },
    setup_requires=[
        'setuptools_scm',
    ],
    install_requires=[
        'funcsigs; python_version < "3"',
    ],
    project_urls={
        'Documentation': 'https://picobox.readthedocs.io',
        'Source': 'https://github.com/ikalnytskyi/picobox',
        'Bugs': 'https://github.com/ikalnytskyi/picobox/issues',
    },
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Libraries',
    ],
)
