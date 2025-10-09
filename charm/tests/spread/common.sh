cleanup_temporal() {
    systemctl stop temporal || true
    rm -rf /etc/systemd/system/temporal.service
    systemctl daemon-reload
}

cleanup_worker() {
    systemctl stop ubuntu-release-worker || true
    rm -rf /etc/systemd/system/ubuntu-release-worker.service
    systemctl daemon-reload
}
