with import <nixpkgs> { };
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
