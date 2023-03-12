from distutils.core import setup, Extension
from Cython.Build import cythonize

def main():
    setup(
        name="CustomProjectManagementModel",
        version="1.0.0",
        description="Cython 学习",
        author="werido",
        author_email="359066432@qq.com",
        ext_modules=cythonize(["CustomProjectManagementModel.py"])

        # ext_modules=cythonize(Extension("test", ["test.py"],language="c"))

    )


if __name__ == "__main__":
    main()
