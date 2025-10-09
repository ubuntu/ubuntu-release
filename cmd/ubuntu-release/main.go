package main

import (
	"log/slog"
	"os"
)

func main() {
	cmd := rootCmd()
	err := cmd.Execute()
	if err != nil {
		slog.Error("ubuntu-release failed", "error", err.Error())
		os.Exit(1)
	}
}
