#!/usr/bin/env bash

set -Eeuo pipefail

readonly PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly DIST_DIR="$PROJECT_ROOT/dist"
readonly BUILD_IMAGE="netbox-cli-deb-builder:ubuntu-20.04"
readonly BUILDER_CONTAINER="netbox-cli-deb-export"
readonly TARGET_UBUNTU_VERSIONS=("20.04" "22.04" "24.04" "26.04")
test_context=""

cleanup() {
    docker rm -f "$BUILDER_CONTAINER" >/dev/null 2>&1 || true
    if [[ -n "$test_context" && -d "$test_context" ]]; then
        rm -rf -- "$test_context"
    fi
}

trap cleanup EXIT

command -v docker >/dev/null 2>&1 || {
    echo "Erro: Docker não está instalado ou não está no PATH." >&2
    exit 1
}

mkdir -p "$DIST_DIR"
find "$DIST_DIR" -maxdepth 1 -type f -name 'netbox-cli_*.deb' -delete

echo "Gerando o pacote no Ubuntu 20.04..."
docker build \
    --file "$PROJECT_ROOT/packaging/deb/Dockerfile.build" \
    --tag "$BUILD_IMAGE" \
    "$PROJECT_ROOT"

cleanup
docker create --name "$BUILDER_CONTAINER" "$BUILD_IMAGE" >/dev/null
docker cp "$BUILDER_CONTAINER:/out/." "$DIST_DIR/"

mapfile -t packages < <(find "$DIST_DIR" -maxdepth 1 -type f -name 'netbox-cli_*.deb' -print)
if (( ${#packages[@]} != 1 )); then
    echo "Erro: esperado exatamente um pacote em $DIST_DIR; encontrados ${#packages[@]}." >&2
    exit 1
fi

package_path="${packages[0]}"
package_relative_path="dist/$(basename "$package_path")"
test_context="$(mktemp -d)"
cp "$PROJECT_ROOT/packaging/deb/Dockerfile.test" "$test_context/Dockerfile"
cp "$package_path" "$test_context/netbox-cli.deb"

echo "Pacote gerado: $package_path"
echo "Testando o mesmo pacote nas versões alvo..."

for ubuntu_version in "${TARGET_UBUNTU_VERSIONS[@]}"; do
    test_image="netbox-cli-deb-test:ubuntu-$ubuntu_version"
    echo "Validando no Ubuntu $ubuntu_version..."
    docker build \
        --build-arg "UBUNTU_VERSION=$ubuntu_version" \
        --tag "$test_image" \
        "$test_context"
done

echo "Compatibilidade validada no Ubuntu ${TARGET_UBUNTU_VERSIONS[*]}."
echo "Instale com: sudo apt install ./$package_relative_path"
