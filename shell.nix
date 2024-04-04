with import <nixpkgs> { };
stdenv.mkDerivation {
  name = "sillyORM";
  buildInputs = [
    python311
  ];
}
