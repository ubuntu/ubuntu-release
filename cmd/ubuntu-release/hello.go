package main

import (
	"log/slog"
	"os"

	"github.com/ubuntu/ubuntu-release/internal/hello"

	"github.com/spf13/cobra"
)

func helloCmd(temporalHost string) *cobra.Command {
	return &cobra.Command{
		Use:           "hello",
		Short:         "Trigger a Hello Ubuntu workflow",
		Long:          "The Hello Ubuntu workflow says Hello to a given product",
		SilenceErrors: true,
		SilenceUsage:  true,
		Run: func(cmd *cobra.Command, args []string) {
			result, err := hello.ExecuteHelloWorkFlow(temporalHost)
			if err != nil {
				slog.Error("failed to execute hello workflow", "error", err)
				os.Exit(1)
			}

			slog.Info(result)
		},
	}
}
