# Workforce Specs

This repository collects Workforce Specifications for Qurrent's production workforces. The purpose of this is to:
1. Create documentation for our projects
2. Provide FDEs with an understanding of how other projects are built and take advatange of succesful design patterns
3. Provide coding agents with references of production-grade specs

The spec is intended to be documented at a level of specificity that would enable an FDE to reproduce the workforce without the need for additional input. Aspirationally, a coding agent provided with documentation of the Qurrent OS could also approximate the implementation.

Specs are generated using Cursor's CLI agent. The bulk of the prompt is in the `spec_creation_prompt.md` at the root of this repository.

If the spec is consistently generated in a suboptimal way across projects, the template should be updated. However, you can get the agent to generate the spec differently for a particular project by adding custom instructions to the 'Custom Instructions' section in the `workforce_spec.md` file for your project. You can also edit the `workforce_spec.md` file directly, and the agent will respect and preserve your preferences.

The spec is created during the deployment process, specifically after a merge into the `main` branch. If for some reason you want to disable spec creation, you can set the flag 'enable-create-spec' to 'false' in the run-standard-cicd job in the `.github/workflows/ci_cd.yaml` file. The agent does not have the ability to write to your repository, only this monorepo.

*Workforce Specs are not intended to be shared with customers*
