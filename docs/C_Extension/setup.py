from distutils.core import setup, Extension
def main():
    setup(
        name="hook",
        version="1.0.0",
        description="Python interface for the fputs C library function",
        author="werido",
        author_email="359066432@qq.com",
        # ext_modules=[Extension("fputs", ["hello.c"])]
        ext_modules=[Extension("hook", ["hook.c"],language="c"),Extension("fputs", ["hello.c"],language="c")]

    )


if __name__ == "__main__":
    main()
