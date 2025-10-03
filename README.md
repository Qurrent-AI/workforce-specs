# Workforce Specs

This repository collects Workforce Specifications for projects in production. The purpose of this is to:

1. Create documentation for our workforces
2. Provide FDEs with an understanding of how other projects are built to take advantage of succesful design patterns when creating new workforces
3. Provide coding agents with references of production-grade workforce implementations

The spec should be documented at a level of specificity that could enable an FDE to reproduce the workforce without the need for much additional input. Aspirationally, a coding agent provided documentation of the Qurrent OS could also approximate the implementation.

The Decision Audit is intended to document the core 'AI Logic' in a detailed but non-technical manner. This section may be useful to Lead AI Strategists as a 'gold standard' for process mapping AI-agent workflows.

Specs are generated using Cursor's CLI agent during our pipeline's CI/CD workflow. The bulk of the prompt is in the `spec_creation_prompt.md` at the root of this repository.

**The structure of the spec may evolve** to include more or less detail as is helpful for FDEs and coding agents. If the spec is consistently generated in a suboptimal way across workforces, the template should be updated. **You can have the agent to generate the spec differently** for a particular project by adding custom instructions to the 'Custom Instructions' section in the `workforce_spec.md` file for your project. You can also edit the `workforce_spec.md` file directly, and the agent will respect and preserve your preferences.

The spec is created during the deployment process after a merge into `main` by a job called `update-workforce-spec`. If for some reason you want to disable spec creation, you can set the flag 'enable-create-spec' to 'false' in the run-standard-cicd job in the `.github/workflows/ci_cd.yaml` file. The agent does not have the ability to write to your repository, only this monorepo.

**At the moment, Workforce Specs are not intended to be shared with customers.**

## Known Issues & Limitations

The pipeline job will fail if the agent's context window is exceeded. The deployement itself will be unaffected by this, but the spec will not be generated. The agent also tends to document larger repositories at a much higher-level of detail, making the workflow spec not very useful. Enhancements to support spec generation for larger codebases are forthcoming.
