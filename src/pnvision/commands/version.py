from importlib.metadata import version as package_version


def get_version() -> str:
    return package_version("pnvision")


if __name__ == "__main__":
    get_version()
