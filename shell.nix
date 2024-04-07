with import <nixpkgs> { };
stdenv.mkDerivation {
  name = "sillyORM";
  buildInputs = [
    python311
    python311Packages.lxml
    # sqlitebrowser
  ];
}
