with import (fetchTarball https://github.com/NixOS/nixpkgs/archive/66adc1e47f8784803f2deb6cacd5e07264ec2d5c.tar.gz) { };
stdenv.mkDerivation {
  name = "sillyORM";
  buildInputs = [
    python311
    python311Packages.lxml
    python311Packages.pylint
    python311Packages.mypy
    python311Packages.pytest
    python311Packages.coverage
    python311Packages.psycopg2
    python311Packages.types-psycopg2
    postgresql_16
    sphinx
    # sqlitebrowser
  ];
}
