package hello

import (
	"context"
	"fmt"
	"log/slog"

	"go.temporal.io/sdk/client"
)

func ExecuteHelloWorkFlow(temporalHost string) (string, error) {
	c, err := client.Dial(client.Options{HostPort: temporalHost})
	if err != nil {
		return "", fmt.Errorf("unable to create temporal client: %w", err)
	}

	defer c.Close()
	options := client.StartWorkflowOptions{
		ID:        "hello-ubuntu-666",
		TaskQueue: UbuntuReleaseTaskQueueName,
	}

	we, err := c.ExecuteWorkflow(context.Background(), options, HelloUbuntu, "ubuntu-desktop")
	if err != nil {
		return "", fmt.Errorf("unable to execute workflow: %w", err)
	}

	slog.Info("workflow info", "workflow_id", we.GetID(), "run_id", we.GetRunID())

	var result string

	err = we.Get(context.Background(), &result)
	if err != nil {
		return "", fmt.Errorf("unable to get workflow result: %w", err)
	}

	return result, nil
}
