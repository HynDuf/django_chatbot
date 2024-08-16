{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "my-django-env";

  buildInputs = [
    pkgs.python310
    pkgs.python310Packages.pip
    pkgs.python310Packages.virtualenv
  ];

  shellHook = ''
    if [ ! -d .venv ]; then
      virtualenv .venv
    fi
    source .venv/bin/activate
  '';
}
