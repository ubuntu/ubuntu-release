package hello

import (
	"time"

	"go.temporal.io/sdk/temporal"
	"go.temporal.io/sdk/workflow"
)

const UbuntuReleaseTaskQueueName = "UBUNTU_RELEASE_TASK_QUEUE"

func HelloUbuntu(ctx workflow.Context, product string) (string, error) {
	// RetryPolicy specifies how to automatically handle retries if an Activity fails.
	retrypolicy := &temporal.RetryPolicy{
		InitialInterval:        time.Second,
		BackoffCoefficient:     2.0,
		MaximumInterval:        100 * time.Second,
		MaximumAttempts:        500, // 0 is unlimited retries
		NonRetryableErrorTypes: []string{"UbuntuReleaseError"},
	}

	options := workflow.ActivityOptions{
		// Timeout options specify when to automatically timeout Activity functions.
		StartToCloseTimeout: time.Minute,
		// Optionally provide a customized RetryPolicy.
		// Temporal retries failed Activities by default.
		RetryPolicy: retrypolicy,
	}

	// Apply the options.
	ctx = workflow.WithActivityOptions(ctx, options)

	var helloOutput string

	helloErr := workflow.ExecuteActivity(ctx, SayHello, product).Get(ctx, &helloOutput)

	if helloErr != nil {
		return "", helloErr
	}

	return "Hello Ubuntu workflow complete", nil
}
