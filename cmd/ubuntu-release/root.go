package main

import (
	"github.com/spf13/cobra"
	"github.com/ubuntu/ubuntu-release/internal/logging"
)

var version = "dev"

func rootCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:           "ubuntu-release",
		Short:         "A Go utility to faciliate the Ubuntu Release activites",
		Version:       version,
		SilenceErrors: true,
		SilenceUsage:  true,
		PreRun: func(cmd *cobra.Command, args []string) {
			logging.ParseLoggingFlags(cmd.Flags())
		},
		Run: func(cmd *cobra.Command, args []string) {
			cmd.Help()
		},
	}

	var temporalHost string

	flags := cmd.PersistentFlags()
	flags.BoolP("verbose", "v", false, "enable verbose logging")
	flags.Bool("trace", false, "enable trace logging")

	flags.StringVar(&temporalHost, "temporal-host", "127.0.0.1:7233", "temporal host")

	cmd.AddCommand(helloCmd(temporalHost))

	return cmd
}
