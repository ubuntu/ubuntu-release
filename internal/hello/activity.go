package hello

import (
	"context"
	"fmt"
	"log/slog"
)

func SayHello(ctx context.Context, product string) (string, error) {
	slog.Info(fmt.Sprintf("Hello %s!", product))
	return "Hello Ubuntu sent out successfully", nil
}
