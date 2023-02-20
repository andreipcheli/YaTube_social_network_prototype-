from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from .models import Post, Group, User, Follow
from django.contrib.auth.decorators import login_required
from .forms import PostForm, CommentForm
from django.views.decorators.cache import cache_page


@cache_page(20, key_prefix='index_page')
def index(request):
    template = 'posts/index.html'
    posts = Post.objects.all().order_by('-pub_date')
    paginator = Paginator(posts, settings.NUM_OF_DISPLAYED_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
    }
    return render(request, template, context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    template = 'posts/group_list.html'
    posts = (Post.objects.filter(group=group).
             order_by('-pub_date'))
    paginator = Paginator(posts, settings.NUM_OF_DISPLAYED_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    # Здесь код запроса к модели и создание словаря контекста
    author = get_object_or_404(User, username=username)
    posts = (Post.objects.filter(author=author).
             order_by('-pub_date'))
    paginator = Paginator(posts, settings.NUM_OF_DISPLAYED_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    post_num = posts.count()
    following = request.user.is_authenticated and Follow.objects.filter(
        user=request.user, author=author).exists()
    context = {
        'post_num': post_num,
        'page_obj': page_obj,
        'author': author,
        'following': following
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    # Здесь код запроса к модели и создание словаря контекста
    post = get_object_or_404(Post, id=post_id)
    author = post.author
    post_num = (Post.objects.filter(author=author).count())
    comments = post.comments.all()
    comment_form = CommentForm(request.POST or None)
    context = {
        'post_num': post_num,
        'post': post,
        'comments': comments,
        'form': comment_form
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST)
    if request.method == 'POST':
        if form.is_valid():
            user = request.user
            form.instance.author = user
            form.save()
            return redirect('posts:profile', user.username)
        return render(request, 'posts/create_post.html', {'form': form})
    form = PostForm()
    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    user = post.author
    if user == request.user:
        if request.method == 'POST':
            form = PostForm(
                request.POST,
                files=request.FILES or None,
                instance=post)
            if form.is_valid():
                form.save()
                return redirect('posts:post_detail', post_id)
            return render(request, 'posts/create_post.html', {'form': form,
                          'is_edit': True, 'post_id': post_id})
        form = PostForm()
        return render(request, 'posts/create_post.html', {'form': form,
                      'is_edit': True, 'post_id': post_id})
    return redirect('posts:post_detail', post_id)


@login_required
def add_comment(request, post_id):
    # Получите пост и сохраните его в переменную post.
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
    posts = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(posts, settings.NUM_OF_DISPLAYED_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    # Подписаться на автора
    author = get_object_or_404(User, username=username)
    user = request.user
    if author != user:
        if not Follow.objects.filter(user=user, author=author).exists():
            Follow.objects.create(
                user=user,
                author=author
            )
    return redirect('posts:follow_index')


@login_required
def profile_unfollow(request, username):
    # Дизлайк, отписка
    author = get_object_or_404(User, username=username)
    user = request.user
    Follow.objects.filter(user=user, author=author).delete()
    return redirect('posts:follow_index')
