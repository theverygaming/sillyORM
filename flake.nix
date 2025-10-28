{
  description = "sillyORM";

  inputs = {
    nixpkgs.url = "nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    { }
    // flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };
      in
      rec {
        packages.default = pkgs.python313Packages.buildPythonPackage rec {
          pname = "sillyORM";
          version = "1.0.0";
          pyproject = true;

          build-system = [
            pkgs.python313Packages.setuptools
          ];

          propagatedBuildInputs = with pkgs; [
            pkgs.python313Packages.alembic
            pkgs.python313Packages.sqlalchemy
          ];

          src = ./.;
        };
        devShells.default = pkgs.stdenv.mkDerivation {
          name = "sillyORM";
          buildInputs =
            with pkgs;
            [
              # lint, fmt, type, docs
              python313Packages.pylint
              python313Packages.mypy
              python313Packages.black
              sphinx
              gnumake

              # test
              python313Packages.coverage
              python313Packages.pytest

              # build
              python313Packages.build

              # postgres
              python313Packages.psycopg2
              python313Packages.types-psycopg2
              postgresql_16

              # xml & web experiments
              python313Packages.lxml

              # for convenience
              sqlitebrowser
            ]
            ++ packages.default.propagatedBuildInputs;
        };
      }
    );
}
