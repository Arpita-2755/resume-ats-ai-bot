from ats_bot.core.pipeline import run_ats_pipeline


def main() -> None:
    jd = """
    We are hiring a Python Backend Developer with FastAPI, Docker, AWS, and SQL skills.
    Candidate should build APIs, optimize performance, and collaborate with product teams.
    """
    resume = """
    Alex Candidate
    alex@email.com | +91-9999999999

    Experience
    - built REST services for internal apps
    - managed deployment pipeline

    Skills
    - Python, Flask, PostgreSQL

    Education
    - B.Tech Computer Science
    """
    analysis, improved_text, file_path = run_ats_pipeline(
        jd_text=jd,
        resume_text=resume,
        template="classic",
        output_format="docx",
    )
    print("Score:", analysis.score)
    print("Preview:", improved_text.splitlines()[:8])
    print("File:", file_path)


if __name__ == "__main__":
    main()

