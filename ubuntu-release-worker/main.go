/*
Copyright © 2025 Florent 'Skia' Jacquet <hyask@ubuntu.com>
*/

package main

import (
	"flag"
	"fmt"
	"log"
	"os"

	"ubuntu-release/lib"

	"go.temporal.io/sdk/client"
	"go.temporal.io/sdk/worker"
)

var Version = "unknown-version"

// @@@SNIPSTART money-transfer-project-template-go-worker
func main() {
	versionPtr := flag.Bool("version", false, "Print the version")
	temporalHostPtr := flag.String("temporal-host", "127.0.0.1:7233", "The Temporal host to connect to")

	flag.Parse()

	if *versionPtr {
		fmt.Println(Version)
		os.Exit(0)
	}

	c, err := client.Dial(client.Options{HostPort: *temporalHostPtr})
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
