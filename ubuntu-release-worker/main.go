/*
Copyright © 2025 Florent 'Skia' Jacquet <hyask@ubuntu.com>
*/

package main

import (
	"log"

	"ubuntu-release/lib"

	"go.temporal.io/sdk/client"
	"go.temporal.io/sdk/worker"
)

// @@@SNIPSTART money-transfer-project-template-go-worker
func main() {

	c, err := client.Dial(client.Options{})
	if err != nil {
		log.Fatalln("Unable to create Temporal client.", err)
	}
	defer c.Close()

	w := worker.New(c, lib.UbuntuReleaseTaskQueueName, worker.Options{})

	// This worker hosts both Workflow and Activity functions.
	w.RegisterWorkflow(lib.HelloUbuntu)
	w.RegisterActivity(lib.SayHello)

	// Start listening to the Task Queue.
	err = w.Run(worker.InterruptCh())
	if err != nil {
		log.Fatalln("unable to start Worker", err)
	}
}

// @@@SNIPEND
