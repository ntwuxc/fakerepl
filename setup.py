from setuptools import setup

setup(name='fakerepl_kernel',
      version='1.1',
      description=' CPP kernel for Jupyter',
      author='fake repl',
      author_email='fakewuxc@ntzx.cn',
      license='MIT',
      classifiers=[
          'License :: OSI Approved :: MIT License',
      ],
      url='https://github.com/ntuwxc/fakerepl/fakerepl_kernel/',
      download_url='https://github.com/ntuwxc/fakerepl/fakerepl_kernel/tarball/1.1',
      packages=['fakerepl_kernel'],
      scripts=['fakerepl/install.py'],
      keywords=['jupyter', 'notebook', 'kernel', 'cpp'],
      include_package_data=True
      )
