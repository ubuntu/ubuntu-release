/*
Copyright © 2025 Utkarsh Gupta <utkarsh@ubuntu.com>
*/

package main

import (
	"context"
	"log"
	"os"
	"ubuntu-release/lib"

	"github.com/spf13/cobra"
	"go.temporal.io/sdk/client"
)

// rootCmd represents the base command when called without any subcommands
var rootCmd = &cobra.Command{
	Use:   "ubuntu-release",
	Short: "A Go utility to faciliate the Ubuntu Release activites",
	//	Long: `A longer description that spans multiple lines and likely contains
	//
	// examples and usage of using your application. For example:
	//
	// Cobra is a CLI library for Go that empowers applications.
	// This application is a tool to generate the needed files
	// to quickly create a Cobra application.`,
	// Uncomment the following line if your bare application
	// has an action associated with it:
	// Run: func(cmd *cobra.Command, args []string) { },
}

var helloCmd = &cobra.Command{
	Use:   "hello",
	Short: "Trigger a Hello Ubuntu workflow",
	Long:  `The Hello Ubuntu workflow says Hello to a given product`,
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.Dial(client.Options{})

		if err != nil {
			log.Fatalln("Unable to create Temporal client:", err)
		}

		defer c.Close()
		options := client.StartWorkflowOptions{
			ID:        "hello-ubuntu-666",
			TaskQueue: lib.UbuntuReleaseTaskQueueName,
		}

		we, err := c.ExecuteWorkflow(context.Background(), options, lib.HelloUbuntu, "ubuntu-desktop")
		if err != nil {
			log.Fatalln("Unable to start the Workflow:", err)
		}

		log.Printf("WorkflowID: %s RunID: %s\n", we.GetID(), we.GetRunID())

		var result string

		err = we.Get(context.Background(), &result)

		if err != nil {
			log.Fatalln("Unable to get Workflow result:", err)
		}

		log.Println(result)
	},
}

// Execute adds all child commands to the root command and sets flags appropriately.
// This is called by main.main(). It only needs to happen once to the rootCmd.
func Execute() {
	err := rootCmd.Execute()
	if err != nil {
		os.Exit(1)
	}
}

func init() {
	// Here you will define your flags and configuration settings.
	// Cobra supports persistent flags, which, if defined here,
	// will be global for your application.

	// rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "config file (default is $HOME/.ubuntu-release.yaml)")

	// Cobra also supports local flags, which will only run
	// when this action is called directly.
	rootCmd.Flags().BoolP("toggle", "t", false, "Help message for toggle")
	rootCmd.AddCommand(helloCmd)
}
func main() {
	Execute()
}
