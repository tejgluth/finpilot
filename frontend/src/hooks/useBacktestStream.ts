import { useBacktestStore } from "../stores/backtestStore";

export function useBacktestStream() {
  return useBacktestStore();
}
