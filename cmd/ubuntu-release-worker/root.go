package main

import (
	"log/slog"
	"os"

	"github.com/spf13/cobra"
	"github.com/ubuntu/ubuntu-release/internal/hello"
	"github.com/ubuntu/ubuntu-release/internal/logging"
)

var version = "dev"

func rootCmd() *cobra.Command {
	return &cobra.Command{
		Use:           "ubuntu-release-worker",
		Short:         "Temporal worker for running Ubuntu Release workflows.",
		Version:       version,
		SilenceErrors: true,
		SilenceUsage:  true,
		PreRun: func(cmd *cobra.Command, args []string) {
			logging.ParseLoggingFlags(cmd.Flags())
		},
		Run: func(cmd *cobra.Command, args []string) {
			var temporalHost string
			flags := cmd.PersistentFlags()
			flags.BoolP("verbose", "v", false, "enable verbose logging")
			flags.Bool("trace", false, "enable trace logging")

			flags.StringVar(&temporalHost, "temporal-host", "127.0.0.1:7233", "Temporal host")

			err := hello.StartHelloWorker(temporalHost)
			if err != nil {
				slog.Error("failed to execute hello workflow", "error", err)
				os.Exit(1)
			}
		},
	}
}
