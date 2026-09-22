# LegoAI Execution Lifecycle

Every LegoAI Execution moves through a fixed lifecycle: created, admitted,
running, and finally exactly one terminal state -- succeeded, failed,
rejected, or cancelled. No capability, including a Model provider call, may
skip a required lifecycle transition.

## Dispatch

Dispatch is the exclusive ordered section where current authorization is
re-checked, Catalog publication is re-confirmed, required evidence is
verified present, and an inert dispatch permit is issued. Dispatch performs
no external effect itself -- it only decides whether an invocation may
proceed.

## Effect Extent

A completed invocation records an EffectExtent: NONE when no external
effect could have occurred, UNKNOWN when a request was sent but its
outcome is uncertain (for example, a timeout), and COMPLETED when a full
response was received. LegoAI never claims a stronger guarantee than the
evidence supports.
