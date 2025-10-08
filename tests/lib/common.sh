start_temporal() {
    sudo snap install temporal
    cat <<-EOF > /etc/systemd/system/temporal.service
[Unit]
Description=Ubuntu Release Temporal server

[Service]
ExecStart=/snap/bin/temporal server start-dev --ip 0.0.0.0 --ui-public-path /ui
Restart=on-failure

[Install]
WantedBy=ubuntu-release-worker.service
EOF
    systemctl daemon-reload
    systemctl start temporal
    # Give the temporal server a chance to start
    for i in $(seq 10); do if ! nc -vw1 localhost 7233; then sleep 1; else break; fi; done
}

start_worker() {
    cat <<-EOF > /etc/systemd/system/ubuntu-release-worker.service
[Unit]
Description=Ubuntu Release Temporal worker

[Service]
User=ubuntu
Group=ubuntu
ExecStart=/usr/bin/ubuntu-release-worker
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl start ubuntu-release-worker
}

remove_temporal() {
    systemctl stop temporal
    rm -f /etc/systemd/system/temporal.service
    sudo snap remove temporal
}

remove_worker() {
    systemctl stop ubuntu-release-worker
    rm -f /etc/systemd/system/ubuntu-release-worker.service
}
