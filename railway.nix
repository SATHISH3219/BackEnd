{ pkgs }:
pkgs.mkShell {
  buildInputs = [
    pkgs.python3  # This ensures that python3 is used
    pkgs.ffmpeg
    pkgs.python3Packages.pip  # Ensures pip is available
  ];
}
