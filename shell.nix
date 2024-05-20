with import (fetchTarball https://github.com/NixOS/nixpkgs/archive/66adc1e47f8784803f2deb6cacd5e07264ec2d5c.tar.gz) { };
stdenv.mkDerivation {
  name = "sillyORM";
  buildInputs = [
    python311

    # lint, fmt, type, docs
    python311Packages.pylint
    python311Packages.mypy
    python311Packages.black
    sphinx
    gnumake

    # test
    python311Packages.coverage
    python311Packages.pytest

    # build
    python311Packages.build

    # postgres
    python311Packages.psycopg2
    python311Packages.types-psycopg2
    postgresql_16

    # xml & web experiments
    python311Packages.lxml

    # for convenience
    sqlitebrowser
  ];
}
