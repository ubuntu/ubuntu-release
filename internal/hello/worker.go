package hello

import (
	"fmt"

	"go.temporal.io/sdk/client"
	"go.temporal.io/sdk/worker"
)

func StartHelloWorker(temporalHost string) error {
	c, err := client.Dial(client.Options{HostPort: temporalHost})
	if err != nil {
		return fmt.Errorf("unable to create temporal client: %w", err)
	}
	defer c.Close()

	w := worker.New(c, UbuntuReleaseTaskQueueName, worker.Options{})

	// This worker hosts both Workflow and Activity functions.
	w.RegisterWorkflow(HelloUbuntu)
	w.RegisterActivity(SayHello)

	// Start listening to the Task Queue.
	err = w.Run(worker.InterruptCh())
	if err != nil {
		return err
	}

	return nil
}
