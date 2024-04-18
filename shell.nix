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
    sphinx
    # sqlitebrowser
  ];
}
