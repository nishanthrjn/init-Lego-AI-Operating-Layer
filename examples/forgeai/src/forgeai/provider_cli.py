"""Explicit operator entry point; no ambient endpoint or credential configuration."""

import argparse
import asyncio
from dataclasses import replace
from pathlib import Path

from legoai.governance.disclosure import DisclosureClass, RepositoryIdentity
from legoai.intelligence.model.values import ProviderId
from legoai.runtime.api import HostError, ModelDeployment, RemoteDisclosureConfig
from legoai_engineering.repository.errors import WorkspaceError
from legoai_engineering.repository.workspace import RepositoryPath

from forgeai.composition import provider_session, summarize_provider_file
from forgeai.provider import ProviderProfile, ReadOnlyApproval
from forgeai.remote import load_profile


async def run(args: argparse.Namespace) -> int:
    mode = ModelDeployment(args.mode)
    policy = None
    if mode is ModelDeployment.REMOTE:
        if args.policy is None or args.custody is None:
            raise ValueError("remote mode requires --policy and --custody")
        synthetic = load_profile(args.policy, synthetic=True)
        if (synthetic.base_url, synthetic.model, synthetic.provider.value) != (
            args.base_url,
            args.model,
            args.provider,
        ):
            raise ValueError("policy recipient must match configured provider")
        policy = synthetic.policy
        if args.target is not None:
            # Declared ceiling is not file approval. Prompt after qualification.
            repository_policy = load_profile(args.policy)
            if repository_policy.repository.value != args.repository_id:
                raise ValueError("repository identity must match policy")
            base = repository_policy.policy.admissions[0]
            addition = synthetic.policy.admissions[0]
            admission = replace(
                base,
                classes=base.classes | {DisclosureClass.SYNTHETIC},
                conditions=base.conditions + addition.conditions,
            )
            policy = RemoteDisclosureConfig(policy.declarations, (admission,))
    profile = ProviderProfile(
        "openai_compatible",
        args.base_url,
        args.model,
        mode,
        ProviderId(args.provider),
        args.timeout,
        "none" if mode is ModelDeployment.LOCAL else "secret_source",
        policy,
        args.custody,
    )
    if args.target is not None and (
        args.repository is None or args.repository_id is None
    ):
        raise ValueError("target requires explicit --repository and --repository-id")
    if args.repository is not None and args.custody is not None:
        if args.custody.resolve().is_relative_to(args.repository.resolve()):
            raise ValueError("custody must be outside the repository")
    with provider_session(profile) as session:
        result = await session.qualify()
        print("synthetic checks:", ",".join(result.checks))
        if result.failure is not None:
            print("failure:", result.failure.value)
            return 1
        print("SYNTHETIC PROVIDER PASS; no quality or repository qualification implied")
        if args.target is not None:
            approval = ReadOnlyApproval(
                RepositoryIdentity(args.repository_id),
                RepositoryPath(args.target),
                profile.model,
                profile.base_url,
            )

            def confirm(value: ReadOnlyApproval) -> bool:
                print(
                    "Separate read/disclosure approval:",
                    args.repository,
                    value.repository.value,
                    value.target.value,
                    value.base_url,
                    value.model,
                    "maximum 16384 bytes; one summary; no mutation",
                )
                return input("Approve this one file? [y/N] ").strip().lower() == "y"

            result = await summarize_provider_file(
                session, args.repository, approval, approve=confirm
            )
            if result.failure is not None:
                print("failure:", result.failure.value)
                return 1
            print("READ-ONLY RESPONSE (untrusted model text):")
            # Escape terminal controls while keeping newlines readable.
            assert result.summary is not None
            print(
                "".join(
                    c if c == "\n" or c.isprintable() else "?" for c in result.summary
                )
            )
            print("response SHA-256:", result.response_digest)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("local", "remote"), required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--custody", type=Path)
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--repository-id")
    parser.add_argument("--target")
    try:
        return asyncio.run(run(parser.parse_args()))
    except WorkspaceError as error:
        print("local source refused:", error.reason.value)
        return 2
    except HostError as error:
        print("governed host refused:", error.failure.value)
        return 2
    except EOFError, KeyboardInterrupt:
        print("operator declined or interrupted; no retry")
        return 130
    except OSError, ValueError, TypeError:
        print("provider configuration or local resource invalid; no retry")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
