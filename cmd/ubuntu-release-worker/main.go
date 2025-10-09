package main

import (
	"os"
)

func main() {
	cmd := rootCmd()
	err := cmd.Execute()
	if err != nil {
		os.Exit(1)
	}
}
