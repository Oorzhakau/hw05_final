from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User


def index(request):
    template = "posts/index.html"
    post_list = Post.objects.all()

    paginator = Paginator(post_list, settings.POST_COUNT)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "index": True,
        "follow": False,
    }
    return render(request, template, context)


def group_posts(request, slug):
    template = "posts/group_list.html"
    group = get_object_or_404(Group, slug=slug)
    post_list = group.group_posts.all()

    paginator = Paginator(post_list, settings.POST_COUNT)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "group": group,
        "page_obj": page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    template = "posts/profile.html"
    author = get_object_or_404(User, username=username)
    post_list = author.posts.all()
    count = post_list.count()

    paginator = Paginator(post_list, settings.POST_COUNT)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    following = request.user.is_authenticated and (
        Follow.objects.filter(user=request.user, author=author).exists()
    )

    context = {
        "author": author,
        "count": count,
        "page_obj": page_obj,
        "following": following,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    template = "posts/post_detail.html"
    post = get_object_or_404(Post, id=post_id)
    author = post.author
    count = author.posts.count()
    form = CommentForm()
    comments = post.comments.all()

    context = {
        "count": count,
        "post": post,
        "form": form,
        "comments": comments,
    }
    return render(request, template, context)


@login_required
def post_create(request):
    template = "posts/create_post.html"
    form = PostForm(
        request.POST or None,
        files=request.FILES or None
    )
    if form.is_valid():
        new_post = form.save(commit=False)
        new_post.author = request.user
        new_post.save()
        return redirect("posts:profile",
                        username=request.user.username)

    context = {"form": form, "is_edit": False}
    return render(request, template, context)


@login_required
def post_edit(request, post_id):
    template = "posts/create_post.html"
    post = get_object_or_404(Post, id=post_id)

    if post.author != request.user:
        return redirect("posts:post_detail", post_id=post.id)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    context = {
        "form": form,
        "is_edit": True,
        "post_id": post_id
    }

    if form.is_valid():
        form.save()
        return redirect("posts:post_detail",
                        post_id=post.id)

    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    template = 'posts/follow.html'
    post_list = Post.objects.filter(
        author__following__user=request.user)

    paginator = Paginator(post_list, settings.POST_COUNT)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "index": False,
        "follow": True,
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    follower = request.user
    following = get_object_or_404(User, username=username)
    if follower != following:
        Follow.objects.get_or_create(user=follower, author=following)
    return redirect("posts:profile", username=username)


@login_required
def profile_unfollow(request, username):
    unfollower = request.user
    following = get_object_or_404(User, username=username)
    relation = Follow.objects.filter(user=unfollower, author=following)
    relation.delete()
    return redirect("posts:profile", username=username)
